# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        """ This migration expexts the PostGIS extension to be available in the
        database. This has to be done by a superuser. It is therefore not possible
        to do this from this migration. The following has to be executed while
        logged on as the postgres user in the database (you might want to use
        sudo su postgres -c 'psql'):

        \c catmaid
        CREATE EXTENSION postgis
        """

        # Add PostGIS edge table
        db.execute('''
            CREATE TABLE treenode_edge (
                id BIGINT PRIMARY KEY,
                edge GEOMETRY(LINESTRINGZ, 0))''')

        # Add edges of available treenodes
        db.execute('''
            INSERT INTO treenode_edge (id, edge) (
                SELECT c.id, ST_MakeLine(
                   ST_MakePoint(c.location_x, c.location_y, c.location_z),
                   ST_MakePoint(p.location_x, p.location_y, p.location_z))
                FROM treenode c JOIN treenode p ON c.parent_id = p.id
                WHERE c.parent_id IS NOT NULL)''')
        # Add self referencing adges for all root nodes
        db.execute('''
            INSERT INTO treenode_edge (id, edge) (
                SELECT r.id, ST_MakeLine(
                   ST_MakePoint(r.location_x, r.location_y, r.location_z),
                   ST_MakePoint(r.location_x, r.location_y, r.location_z))
                FROM treenode r
                WHERE r.parent_id IS NULL)''')

        # Add 3D index, which seems to be faster in our situation
        # A 2D index can be created with:
        # CREATE INDEX treenode_edge_gix ON treenode_edge USING GIST (edge)
        db.execute('''
            CREATE INDEX treenode_edge_gix ON treenode_edge
                USING GIST (edge gist_geometry_ops_nd)''')

        # Add trigger for inserting treenodes. If the inserted node doesn't
        # have a parent node, a zero-length edge is inserted.
        db.execute('''
            CREATE FUNCTION on_insert_treenode_update_edges() RETURNS trigger\n
            LANGUAGE plpgsql\n
            AS $$BEGIN\n
            INSERT INTO treenode_edge (id, edge) (
                SELECT c.id, ST_MakeLine(
                    ST_MakePoint(c.location_x, c.location_y, c.location_z),
                    ST_MakePoint(p.location_x, p.location_y, p.location_z))
                FROM treenode c JOIN treenode p ON
                    (c.parent_id = p.id) OR (c.parent_id IS NULL AND c.id = p.id)
                WHERE c.id=NEW.id);
            RETURN NEW;
            END;
            $$;''')
        db.execute('''
            CREATE TRIGGER on_insert_treenode_update_edges
            AFTER INSERT ON treenode
            FOR EACH ROW EXECUTE PROCEDURE on_insert_treenode_update_edges()''')

        # Add triggers for updating treenodes. Existing edges that involve the
        # node as child are only re-created if the location or the parent
        # changed.
        db.execute('''
            CREATE FUNCTION on_edit_treenode_update_edges() RETURNS trigger\n
            LANGUAGE plpgsql\n
            AS $$BEGIN\n
            if OLD.location_x != NEW.location_x OR OLD.location_y != NEW.location_y OR
                    OLD.location_z != NEW.location_z OR OLD.parent_id != NEW.parent_id then
                DELETE FROM treenode_edge WHERE id=OLD.id;
            end if;
            INSERT INTO treenode_edge (id, edge) (
                SELECT NEW.id, ST_MakeLine(
                    ST_MakePoint(NEW.location_x, NEW.location_y, NEW.location_z),
                    ST_MakePoint(p.location_x, p.location_y, p.location_z))
                FROM treenode p
                WHERE (p.id = NEW.parent_id) OR (NEW.parent_id IS NULL AND NEW.id = p.id));
            RETURN NEW;
            END;
            $$;''')
        db.execute('''
            CREATE TRIGGER on_edit_treenode_update_edges
            AFTER UPDATE ON treenode
            FOR EACH ROW EXECUTE PROCEDURE on_edit_treenode_update_edges()''')

        # Add on_delete trigger for treenodes. If a treenode is deleted, all
        # edges involving it as a child are removed. Treenodes where the
        # removed one is a parent, require a client side update anyway (to
        # change the parent). And if this happens, their update trigger will
        # kick in.
        db.execute('''
            CREATE FUNCTION on_delete_treenode_update_edges() RETURNS trigger\n
                LANGUAGE plpgsql\n
                AS $$BEGIN\n
                DELETE FROM treenode_edge WHERE id=OLD.id;
                RETURN OLD;
            END;
            $$;''')
        db.execute('''
            CREATE TRIGGER on_delete_treenode_update_edges
            BEFORE DELETE ON treenode
            FOR EACH ROW EXECUTE PROCEDURE on_delete_treenode_update_edges()''')

    def backwards(self, orm):
        db.execute('DROP INDEX treenode_edge_gix')
        db.execute('DROP TABLE treenode_edge')
        db.execute('DROP TRIGGER on_insert_treenode_update_edges ON treenode')
        db.execute('DROP TRIGGER on_edit_treenode_update_edges ON treenode')
        db.execute('DROP TRIGGER on_delete_treenode_update_edges ON treenode')
        db.execute('DROP FUNCTION on_insert_treenode_update_edges()')
        db.execute('DROP FUNCTION on_edit_treenode_update_edges()')
        db.execute('DROP FUNCTION on_delete_treenode_update_edges()')

    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'catmaid.apikey': {
            'Meta': {'object_name': 'ApiKey'},
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'catmaid.brokenslice': {
            'Meta': {'object_name': 'BrokenSlice', 'db_table': "'broken_slice'"},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.IntegerField', [], {}),
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Stack']"})
        },
        u'catmaid.cardinalityrestriction': {
            'Meta': {'object_name': 'CardinalityRestriction', 'db_table': "'cardinality_restriction'"},
            'cardinality_type': ('django.db.models.fields.IntegerField', [], {}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'restricted_link': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.ClassClass']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'value': ('django.db.models.fields.IntegerField', [], {})
        },
        u'catmaid.changerequest': {
            'Meta': {'object_name': 'ChangeRequest', 'db_table': "'change_request'"},
            'approve_action': ('django.db.models.fields.TextField', [], {}),
            'completion_time': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'connector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Connector']"}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('catmaid.fields.Double3DField', [], {}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'recipient': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'change_recipient'", 'db_column': "'recipient_id'", 'to': u"orm['auth.User']"}),
            'reject_action': ('django.db.models.fields.TextField', [], {}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'treenode': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Treenode']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'validate_action': ('django.db.models.fields.TextField', [], {})
        },
        u'catmaid.class': {
            'Meta': {'object_name': 'Class', 'db_table': "'class'"},
            'class_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'catmaid.classclass': {
            'Meta': {'object_name': 'ClassClass', 'db_table': "'class_class'"},
            'class_a': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'classes_a'", 'db_column': "'class_a'", 'to': u"orm['catmaid.Class']"}),
            'class_b': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'classes_b'", 'db_column': "'class_b'", 'to': u"orm['catmaid.Class']"}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'relation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Relation']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'catmaid.classinstance': {
            'Meta': {'object_name': 'ClassInstance', 'db_table': "'class_instance'"},
            'class_column': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Class']", 'db_column': "'class_id'"}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'catmaid.classinstanceclassinstance': {
            'Meta': {'object_name': 'ClassInstanceClassInstance', 'db_table': "'class_instance_class_instance'"},
            'class_instance_a': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cici_via_a'", 'db_column': "'class_instance_a'", 'to': u"orm['catmaid.ClassInstance']"}),
            'class_instance_b': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cici_via_b'", 'db_column': "'class_instance_b'", 'to': u"orm['catmaid.ClassInstance']"}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'relation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Relation']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'catmaid.concept': {
            'Meta': {'object_name': 'Concept', 'db_table': "'concept'"},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'catmaid.connector': {
            'Meta': {'object_name': 'Connector', 'db_table': "'connector'"},
            'confidence': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'editor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'connector_editor'", 'db_column': "'editor_id'", 'to': u"orm['auth.User']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location_x': ('django.db.models.fields.FloatField', [], {}),
            'location_y': ('django.db.models.fields.FloatField', [], {}),
            'location_z': ('django.db.models.fields.FloatField', [], {}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'catmaid.connectorclassinstance': {
            'Meta': {'object_name': 'ConnectorClassInstance', 'db_table': "'connector_class_instance'"},
            'class_instance': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.ClassInstance']"}),
            'connector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Connector']"}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'relation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Relation']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'catmaid.dataview': {
            'Meta': {'ordering': "('position',)", 'object_name': 'DataView', 'db_table': "'data_view'"},
            'comment': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'config': ('django.db.models.fields.TextField', [], {'default': "'{}'"}),
            'data_view_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.DataViewType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_default': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'position': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'title': ('django.db.models.fields.TextField', [], {})
        },
        u'catmaid.dataviewtype': {
            'Meta': {'object_name': 'DataViewType', 'db_table': "'data_view_type'"},
            'code_type': ('django.db.models.fields.TextField', [], {}),
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.TextField', [], {})
        },
        u'catmaid.deprecatedappliedmigrations': {
            'Meta': {'object_name': 'DeprecatedAppliedMigrations', 'db_table': "'applied_migrations'"},
            'id': ('django.db.models.fields.CharField', [], {'max_length': '32', 'primary_key': 'True'})
        },
        u'catmaid.deprecatedsession': {
            'Meta': {'object_name': 'DeprecatedSession', 'db_table': "'sessions'"},
            'data': ('django.db.models.fields.TextField', [], {'default': "''"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_accessed': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'session_id': ('django.db.models.fields.CharField', [], {'max_length': '26'})
        },
        u'catmaid.location': {
            'Meta': {'object_name': 'Location', 'db_table': "'location'"},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'editor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'location_editor'", 'db_column': "'editor_id'", 'to': u"orm['auth.User']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location_x': ('django.db.models.fields.FloatField', [], {}),
            'location_y': ('django.db.models.fields.FloatField', [], {}),
            'location_z': ('django.db.models.fields.FloatField', [], {}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'catmaid.log': {
            'Meta': {'object_name': 'Log', 'db_table': "'log'"},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'freetext': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('catmaid.fields.Double3DField', [], {}),
            'operation_type': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'catmaid.message': {
            'Meta': {'object_name': 'Message', 'db_table': "'message'"},
            'action': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'read': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'text': ('django.db.models.fields.TextField', [], {'default': "'New message'", 'null': 'True', 'blank': 'True'}),
            'time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'title': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'catmaid.overlay': {
            'Meta': {'object_name': 'Overlay', 'db_table': "'overlay'"},
            'default_opacity': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'file_extension': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_base': ('django.db.models.fields.TextField', [], {}),
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Stack']"}),
            'tile_height': ('django.db.models.fields.IntegerField', [], {'default': '512'}),
            'tile_source_type': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'tile_width': ('django.db.models.fields.IntegerField', [], {'default': '512'}),
            'title': ('django.db.models.fields.TextField', [], {})
        },
        u'catmaid.project': {
            'Meta': {'object_name': 'Project', 'db_table': "'project'"},
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stacks': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['catmaid.Stack']", 'through': u"orm['catmaid.ProjectStack']", 'symmetrical': 'False'}),
            'title': ('django.db.models.fields.TextField', [], {})
        },
        u'catmaid.projectstack': {
            'Meta': {'object_name': 'ProjectStack', 'db_table': "'project_stack'"},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'orientation': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Stack']"}),
            'translation': ('catmaid.fields.Double3DField', [], {'default': '(0, 0, 0)'})
        },
        u'catmaid.regionofinterest': {
            'Meta': {'object_name': 'RegionOfInterest', 'db_table': "'region_of_interest'"},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'editor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'roi_editor'", 'db_column': "'editor_id'", 'to': u"orm['auth.User']"}),
            'height': ('django.db.models.fields.FloatField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location_x': ('django.db.models.fields.FloatField', [], {}),
            'location_y': ('django.db.models.fields.FloatField', [], {}),
            'location_z': ('django.db.models.fields.FloatField', [], {}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'rotation_cw': ('django.db.models.fields.FloatField', [], {}),
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Stack']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'width': ('django.db.models.fields.FloatField', [], {}),
            'zoom_level': ('django.db.models.fields.IntegerField', [], {})
        },
        u'catmaid.regionofinterestclassinstance': {
            'Meta': {'object_name': 'RegionOfInterestClassInstance', 'db_table': "'region_of_interest_class_instance'"},
            'class_instance': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.ClassInstance']"}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'region_of_interest': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.RegionOfInterest']"}),
            'relation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Relation']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'catmaid.relation': {
            'Meta': {'object_name': 'Relation', 'db_table': "'relation'"},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'isreciprocal': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'relation_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uri': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'catmaid.relationinstance': {
            'Meta': {'object_name': 'RelationInstance', 'db_table': "'relation_instance'"},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'relation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Relation']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'catmaid.restriction': {
            'Meta': {'object_name': 'Restriction', 'db_table': "'restriction'"},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'restricted_link': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.ClassClass']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'catmaid.review': {
            'Meta': {'object_name': 'Review', 'db_table': "'review'"},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'review_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'reviewer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'skeleton': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.ClassInstance']"}),
            'treenode': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Treenode']"})
        },
        u'catmaid.settings': {
            'Meta': {'object_name': 'Settings', 'db_table': "'settings'"},
            'key': ('django.db.models.fields.TextField', [], {'primary_key': 'True'}),
            'value': ('django.db.models.fields.TextField', [], {'null': 'True'})
        },
        u'catmaid.stack': {
            'Meta': {'object_name': 'Stack', 'db_table': "'stack'"},
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'dimension': ('catmaid.fields.Integer3DField', [], {}),
            'file_extension': ('django.db.models.fields.TextField', [], {'default': "'jpg'", 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_base': ('django.db.models.fields.TextField', [], {}),
            'metadata': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'num_zoom_levels': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'resolution': ('catmaid.fields.Double3DField', [], {}),
            'tile_height': ('django.db.models.fields.IntegerField', [], {'default': '256'}),
            'tile_source_type': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'tile_width': ('django.db.models.fields.IntegerField', [], {'default': '256'}),
            'title': ('django.db.models.fields.TextField', [], {}),
            'trakem2_project': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'catmaid.textlabel': {
            'Meta': {'object_name': 'Textlabel', 'db_table': "'textlabel'"},
            'colour': ('catmaid.fields.RGBAField', [], {'default': '(1, 0.5, 0, 1)'}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'font_name': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'font_size': ('django.db.models.fields.FloatField', [], {'default': '32'}),
            'font_style': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'scaling': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {'default': "'Edit this text ...'"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        u'catmaid.textlabellocation': {
            'Meta': {'object_name': 'TextlabelLocation', 'db_table': "'textlabel_location'"},
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('catmaid.fields.Double3DField', [], {}),
            'textlabel': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Textlabel']"})
        },
        u'catmaid.treenode': {
            'Meta': {'object_name': 'Treenode', 'db_table': "'treenode'"},
            'confidence': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'editor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'treenode_editor'", 'db_column': "'editor_id'", 'to': u"orm['auth.User']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location_x': ('django.db.models.fields.FloatField', [], {}),
            'location_y': ('django.db.models.fields.FloatField', [], {}),
            'location_z': ('django.db.models.fields.FloatField', [], {}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'children'", 'null': 'True', 'to': u"orm['catmaid.Treenode']"}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'radius': ('django.db.models.fields.FloatField', [], {}),
            'skeleton': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.ClassInstance']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'catmaid.treenodeclassinstance': {
            'Meta': {'object_name': 'TreenodeClassInstance', 'db_table': "'treenode_class_instance'"},
            'class_instance': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.ClassInstance']"}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'relation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Relation']"}),
            'treenode': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Treenode']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'catmaid.treenodeconnector': {
            'Meta': {'object_name': 'TreenodeConnector', 'db_table': "'treenode_connector'"},
            'confidence': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'connector': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Connector']"}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'relation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Relation']"}),
            'skeleton': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.ClassInstance']"}),
            'treenode': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Treenode']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'catmaid.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'color': ('catmaid.fields.RGBAField', [], {'default': '(1, 0, 0.5, 1)'}),
            'display_stack_reference_lines': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'independent_ontology_workspace_is_default': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'inverse_mouse_wheel': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'show_cropping_tool': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'show_ontology_tool': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'show_roi_tool': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'show_segmentation_tool': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'show_tagging_tool': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'show_text_label_tool': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'show_tracing_tool': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'tracing_overlay_scale': ('django.db.models.fields.FloatField', [], {'default': '1'}),
            'tracing_overlay_screen_scaling': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['catmaid']
